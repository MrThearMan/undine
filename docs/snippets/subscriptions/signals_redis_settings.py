CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [("127.0.0.1", 6379)],
        },
    },
}

UNDINE = {
    "SUBSCRIPTION_BROKER_CLASS": "undine.integrations.channels.ChannelLayerSubscriptionBroker",
}
