package com.example.insight.common.constants

class ApiMessages {
    object Common {
        const val error500 = "Something went wrong"
        const val error400 = "Bad request"
        const val error401 = "Unauthorized request"
        const val error403 = "Forbidden request"
        const val success200 = "Success"
        const val error404 = "Not record found"
        const val vendorError = "Please try again. If the issue persists then contact us."
    }

    object Article {
        const val notFound = "Article not found"
        const val insertError = "Unable to insert the article"
    }

    object ArticleSource {
        const val notFound = "Article source not found"
    }

    object Podcast {
        const val notFound = "Podcast not found"
    }

    object Authentication {
        const val invalidOTP = "Invalid OTP"
        const val invalidMobileNumber = "Invalid Mobile Number"
        const val expiredAuthToken = "Session expired. Please login again!"
        const val otpGenerated = "OTP generated successfully"
        const val otpResent = "OTP resent successfully"
    }

    object ArticleSearch {
        const val INVALID_SEARCH_QUERY = "Please enter a valid search query!"
    }

    object User {
        const val INVALID_USER_NAME = "Please enter a valid user name!"
    }
}