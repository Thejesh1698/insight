package com.example.insight.features.eventsManager.utils

class EventConstants {

    enum class EventPropertyKeys(val mixpanelKey: String?, footPrintsKey: String?) {
        VENDOR_KEY_INSERT_ID("\$insert_id", null),
        VENDOR_KEY_TIME("time", null),
        VENDOR_KEY_DISTINCT_ID("distinct_id", null),
        PLATFORM_TYPE("Platform Type", "Platform Type"),
        APP_VERSION("App Version", "App Version"),
        APP_BUILD_NUMBER("App Build Number", "App Build Number"),
        DEVICE_BRAND("Device Brand", "Device Brand"),
        DEVICE_MANUFACTURER("Device Manufacturer", "Device Manufacturer"),
        USER_ID("User ID", null),
        USER_NAME("Name", null),
        USER_PHONE_NUMBER("Phone Number", null),
        USER_EMAIL("Email", null)
    }

    enum class EventNames(val mixpanelName: String?, val footPrintName: String?) {
        USER_SIGNUP("Sign Up", null),
        USER_LOGIN("Log In", null),
    }

    enum class UserPropertyKeys(val value: String) {
        USER_ID("User ID"),
        USER_NAME("name"),
        USER_PHONE_NUMBER("Phone Number"),
        USER_EMAIL("email"),
        SIGN_UP_TYPE("Sign Up Type")
    }

    object EventsRequestContextProperties {

        enum class HeaderNames {
            PLATFORM_TYPE,
            APP_VERSION,
            APP_BUILD_NUMBER,
            DEVICE_BRAND,
            DEVICE_MANUFACTURER,
            REFERER
        }
    }
}