package com.example.insight.common.utils

fun isMobileNumberValid(number: String): Boolean {

    val mobileNumberRegex = Regex("^[6-9][0-9]{9}$")
    return mobileNumberRegex.matches(number)
}

fun isValidUserName(userName: String): Boolean {
    // Regular expression to allow only text and spaces
    val regex = "^[a-zA-Z\\s]+$".toRegex()
    return regex.matches(userName)
}