package com.example.insight.common.errorHandler

class ErrorTypes {
    enum class Http5xxErrors {
        INTERNAL_SERVER_ERROR;
    }

    enum class Http4xxErrors {
        BAD_REQUEST, NOT_FOUND;

        enum class Authentication{
            NOT_AUTHORIZED, EXPIRED_AUTH_TOKEN, INVALID_OTP, INVALID_MOBILE_NUMBER, EXPIRED_OTP, OTP_VERIFY_TRIES_MAX_REACHED, OTP_RETRY_MAX_REACHED, FORBIDDEN_REQUEST;
        }

        enum class ArticleSearch{
            INVALID_SEARCH_QUERY
        }

        enum class User{
            INVALID_USER_NAME
        }
    }
}