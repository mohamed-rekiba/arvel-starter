from __future__ import annotations

from app.providers.auth_provider import AuthProvider
from app.providers.data_provider import DataProvider
from app.providers.event_provider import EventProvider
from app.providers.observability_provider import StarterObservabilityProvider
from arvel.broadcasting.provider import BroadcastServiceProvider
from arvel.data.provider import DatabaseServiceProvider
from arvel.http.provider import HttpServiceProvider
from arvel.infra.provider import InfrastructureProvider
from arvel.media.provider import MediaProvider
from arvel.observability.provider import ObservabilityProvider
from arvel.queue.provider import QueueProvider
from arvel.search.provider import SearchProvider
from arvel.security.provider import SecurityProvider

providers = [
    ObservabilityProvider,
    DatabaseServiceProvider,
    DataProvider,
    InfrastructureProvider,
    QueueProvider,
    SecurityProvider,
    AuthProvider,
    EventProvider,
    SearchProvider,
    BroadcastServiceProvider,
    MediaProvider,
    StarterObservabilityProvider,
    HttpServiceProvider,
]
