# Forms package

from .auth import LoginForm, PasswordChangeForm
from .monitor import MonitorForm, MonitorEditForm
from .monitor_notification import MonitorNotificationForm
from .notification import (
    NotificationChannelForm,
    NotificationChannelEditForm,
    TestNotificationForm,
)
from .oidc import OIDCProviderForm
from .public_status import PublicStatusPageForm, PublicStatusPageEditForm

__all__ = [
    "LoginForm",
    "RegistrationForm",
    "PasswordChangeForm",
    "MonitorForm",
    "MonitorEditForm",
    "NotificationChannelForm",
    "NotificationChannelEditForm",
    "MonitorNotificationForm",
    "TestNotificationForm",
    "OIDCProviderForm",
    "PublicStatusPageForm",
    "PublicStatusPageEditForm",
]
