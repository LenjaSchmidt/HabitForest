from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "external_steps.json"
GOOGLE_FIT_SCOPE = "https://www.googleapis.com/auth/fitness.activity.read"
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_FIT_AGGREGATE_URL = "https://www.googleapis.com/fitness/v1/users/me/dataset:aggregate"
GOOGLE_FIT_ESTIMATED_STEPS_SOURCE = "derived:com.google.step_count.delta:com.google.android.gms:estimated_steps"


def _parse_steps(raw_value) -> int:
    """Accept ints, numeric strings, and strings with separators like '11,000'."""

    if raw_value is None:
        return 0
    if isinstance(raw_value, (int, float)):
        return int(raw_value)
    cleaned = str(raw_value).strip().replace(",", "").replace("_", "")
    if not cleaned:
        return 0
    try:
        return int(float(cleaned))
    except ValueError:
        return 0


def _json_request(url: str, method: str = "GET", headers: dict | None = None, data: dict | None = None) -> dict:
    payload = None
    request_headers = headers.copy() if headers else {}
    if data is not None:
        payload = json.dumps(data).encode("utf-8")
        request_headers.setdefault("Content-Type", "application/json")
    request = Request(url, data=payload, headers=request_headers, method=method)
    with urlopen(request, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def _form_request(url: str, data: dict) -> dict:
    encoded = urlencode(data).encode("utf-8")
    request = Request(
        url,
        data=encoded,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urlopen(request, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


@dataclass(frozen=True)
class StepSnapshot:
    date: str
    steps: int
    source: str
    synced_at: str
    connected: bool
    error: str = ""
    provider_used: str = ""
    raw_response: dict | None = None
    data_source_names: tuple[str, ...] = ()
    fallback_active: bool = False
    notice: str = ""


class StepTrackerProvider:
    """Base contract for external step providers used by the MVP integration layer."""

    def get_today_snapshot(self) -> StepSnapshot:
        raise NotImplementedError


class SimulatedStepTrackerProvider(StepTrackerProvider):
    """Demo provider backed by a local JSON payload."""

    def __init__(self, data_path: Path = DATA_PATH):
        self.data_path = data_path

    def get_today_snapshot(self) -> StepSnapshot:
        today = date.today().isoformat()
        synced_at = datetime.now().strftime("%H:%M")
        payload = self._load_payload()
        if payload and payload.get("date") == today:
            return StepSnapshot(
                date=today,
                steps=max(0, _parse_steps(payload.get("steps", 0))),
                source=str(payload.get("source") or "Demo step data"),
                synced_at=synced_at,
                connected=False,
                error="",
                provider_used="JSON Fallback",
                raw_response=payload,
                data_source_names=(),
                fallback_active=True,
                notice="",
            )
        return self._fallback_snapshot(today, synced_at)

    def _load_payload(self) -> dict | None:
        if not self.data_path.exists():
            return None
        try:
            return json.loads(self.data_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError, ValueError):
            return None

    def _fallback_snapshot(self, today: str, synced_at: str) -> StepSnapshot:
        weekday = date.today().weekday()
        fallback_steps = [10432, 7850, 11208, 9320, 12144, 8764, 9980][weekday]
        return StepSnapshot(
            date=today,
            steps=fallback_steps,
            source="Demo step data",
            synced_at=synced_at,
            connected=False,
            error="Using fallback step data.",
            provider_used="JSON Fallback",
            raw_response=None,
            data_source_names=(),
            fallback_active=True,
            notice="",
        )


class GoogleFitOAuthError(Exception):
    pass


def build_google_fit_auth_url(client_id: str, redirect_uri: str, state: str) -> str:
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": GOOGLE_FIT_SCOPE,
        "access_type": "offline",
        "prompt": "consent",
        "include_granted_scopes": "true",
        "state": state,
    }
    return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"


def exchange_google_fit_code(code: str, client_id: str, client_secret: str, redirect_uri: str) -> dict:
    try:
        token_payload = _form_request(
            GOOGLE_TOKEN_URL,
            {
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
        )
    except (HTTPError, URLError, json.JSONDecodeError) as exc:
        raise GoogleFitOAuthError("Google Fit login could not be completed.") from exc
    token_payload["obtained_at"] = int(datetime.now().timestamp())
    return token_payload


def refresh_google_fit_token(tokens: dict, client_id: str, client_secret: str) -> dict:
    refresh_token = tokens.get("refresh_token")
    if not refresh_token:
        raise GoogleFitOAuthError("Google Fit needs to be connected again.")
    try:
        refreshed = _form_request(
            GOOGLE_TOKEN_URL,
            {
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
        )
    except (HTTPError, URLError, json.JSONDecodeError) as exc:
        raise GoogleFitOAuthError("Google Fit session could not be refreshed.") from exc
    refreshed["refresh_token"] = refresh_token
    refreshed["obtained_at"] = int(datetime.now().timestamp())
    return refreshed


def token_expired(tokens: dict) -> bool:
    expires_in = int(tokens.get("expires_in", 0) or 0)
    obtained_at = int(tokens.get("obtained_at", 0) or 0)
    if not expires_in or not obtained_at:
        return True
    return int(datetime.now().timestamp()) >= (obtained_at + expires_in - 60)


class GoogleFitStepTrackerProvider(StepTrackerProvider):
    """Google Fit-backed provider.

    Google Fit is deprecated for new Android health integrations. A future mobile
    implementation should preferably move to Health Connect, but this provider
    gives the HabitForest MVP a real OAuth + Google Fitness REST path today.
    """

    def __init__(self, tokens: dict, client_id: str, client_secret: str):
        self.tokens = tokens
        self.client_id = client_id
        self.client_secret = client_secret
        self.updated_tokens = tokens

    def get_today_snapshot(self) -> StepSnapshot:
        today = date.today().isoformat()
        synced_at = datetime.now().strftime("%H:%M")
        tokens = self.tokens
        if token_expired(tokens):
            tokens = refresh_google_fit_token(tokens, self.client_id, self.client_secret)
            self.updated_tokens = tokens
        access_token = tokens.get("access_token")
        if not access_token:
            raise GoogleFitOAuthError("Google Fit is not connected.")

        local_now = datetime.now().astimezone()
        start_of_day = datetime.combine(local_now.date(), time.min, tzinfo=local_now.tzinfo)
        end_of_day = start_of_day + timedelta(days=1)
        body = {
            "aggregateBy": [{"dataTypeName": "com.google.step_count.delta"}],
            "bucketByTime": {"durationMillis": 86400000},
            "startTimeMillis": int(start_of_day.timestamp() * 1000),
            "endTimeMillis": int(end_of_day.timestamp() * 1000),
        }
        try:
            response = _json_request(
                GOOGLE_FIT_AGGREGATE_URL,
                method="POST",
                headers={"Authorization": f"Bearer {access_token}"},
                data=body,
            )
        except HTTPError as exc:
            if exc.code == 401:
                refreshed = refresh_google_fit_token(tokens, self.client_id, self.client_secret)
                self.updated_tokens = refreshed
                response = _json_request(
                    GOOGLE_FIT_AGGREGATE_URL,
                    method="POST",
                    headers={"Authorization": f"Bearer {refreshed.get('access_token', '')}"},
                    data=body,
                )
            else:
                raise GoogleFitOAuthError("Google Fit data could not be loaded.") from exc
        except (URLError, json.JSONDecodeError) as exc:
            raise GoogleFitOAuthError("Google Fit data could not be loaded.") from exc

        steps = 0
        data_source_names = set()
        for bucket in response.get("bucket", []):
            for dataset in bucket.get("dataset", []):
                for point in dataset.get("point", []):
                    source_name = point.get("originDataSourceId") or point.get("dataSourceId")
                    if source_name:
                        data_source_names.add(str(source_name))
                    for value in point.get("value", []):
                        steps += _parse_steps(value.get("intVal", 0))

        notice = ""
        if steps == 0:
            notice = "Fitbit data is visible in the Fitbit app but not available through Google Fit yet."

        return StepSnapshot(
            date=today,
            steps=max(0, steps),
            source="Google Fit",
            synced_at=synced_at,
            connected=True,
            error="",
            provider_used="Google Fit",
            raw_response=response,
            data_source_names=tuple(sorted(data_source_names)),
            fallback_active=False,
            notice=notice,
        )


class HealthConnectStepTrackerProvider(StepTrackerProvider):
    """Future Android provider placeholder."""

    def get_today_snapshot(self) -> StepSnapshot:
        raise NotImplementedError("Health Connect integration is not implemented in this MVP.")
