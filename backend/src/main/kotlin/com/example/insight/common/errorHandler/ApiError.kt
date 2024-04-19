package com.example.insight.common.errorHandler

import com.fasterxml.jackson.annotation.JsonFormat
import com.example.insight.common.errorHandler.exceptions.CustomException
import java.util.*


/**
 * The class *ApiError* and it's implementations
 * (ex: *GlobalExceptionHandler* ) are used to handle all exceptions at one place
 * and throw the api errors to the clients in a much more descriptive way!
 *
 * This class has few variables initialised based on the environment aka errorStackTrace
 * and few other variables initialised from the constructor.
 * ######
 * @see     GlobalExceptionHandler
 * @since   kotlin 1.8.22
 */
class ApiError(exception: CustomException) {
    val errorCode: Int
    val errorType: String
    val message: String

    /**
     * This flag can be used in the frontend to decide whether to show the error to the user or not.
     */
    val notifyUser: Boolean

    /**
     * This variable is used to store stack trace and is only being initialised
     * based on environment. Hence, it will be null in prod which will help us
     * not to expose the schema to the users.
     */
    var errorStackTrace: String? = null

    @JsonFormat(shape = JsonFormat.Shape.STRING, pattern = "dd-MM-yyyy hh:mm:ss")
    val timestamp: Date = Date()

    init {
        errorCode = exception.httpStatus.value()
        this.errorType = exception.errorType.toString()
        this.message = exception.message
        this.notifyUser = exception.notifyUser
        val serverType = System.getenv("ENV_TYPE")?: "beta"
        if(serverType == "local" || serverType == "beta"){
            errorStackTrace = exception.stackTrace.joinToString("\n")
        }
    }
}