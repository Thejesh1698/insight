package com.example.insight.common.errorHandler.exceptions

import org.springframework.http.HttpStatus

abstract class CustomException : RuntimeException() {
    /**
     * The choices for types of errorType are inner classes of ErrorTypes
     * @see ErrorTypes
     */
    abstract val errorType: Any
    abstract override var message: String
    abstract val notifyUser: Boolean
    abstract var httpStatus: HttpStatus
}