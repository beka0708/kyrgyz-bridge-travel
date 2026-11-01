from .base import *  # noqa: F403

DEBUG = True
DESIGN_SWITCH = env.bool("DESIGN_SWITCH", default=True)  # noqa: F405
ALLOWED_HOSTS = ["*"]
