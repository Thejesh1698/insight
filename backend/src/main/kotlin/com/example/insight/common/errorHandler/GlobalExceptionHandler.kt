package com.example.insight.common.errorHandler

import com.example.insight.common.errorHandler.exceptions.*
import org.springframework.http.ResponseEntity
import org.springframework.web.bind.annotation.ControllerAdvice
import org.springframework.web.bind.annotation.ExceptionHandler
import org.springframework.web.servlet.mvc.method.annotation.ResponseEntityExceptionHandler


@ControllerAdvice
class GlobalExceptionHandle: ResponseEntityExceptionHandler() {

    private fun buildResponseEntity(exception: CustomException): ResponseEntity<Any?> {

        val apiError = ApiError(exception)
        return ResponseEntity(apiError, exception.httpStatus)
    }

    @ExceptionHandler(UnauthorizedException::class)
    fun handleUnauthorizedException(exception: UnauthorizedException): ResponseEntity<Any?> {

        return buildResponseEntity(exception)
    }

    @ExceptionHandler(InternalServerErrorException::class)
    fun handleInternalServerException(exception: InternalServerErrorException): ResponseEntity<Any?> {

        return buildResponseEntity(exception)
    }

    @ExceptionHandler(NoRecordFoundException::class)
    fun handleNoRecordFoundException(exception: NoRecordFoundException): ResponseEntity<Any?> {

        return buildResponseEntity(exception)
    }

    @ExceptionHandler(BadRequestException::class)
    fun handleBadRequestException(exception: BadRequestException): ResponseEntity<Any?> {

        return buildResponseEntity(exception)
    }

    @ExceptionHandler(ForbiddenRequestException::class)
    fun handleBadRequestException(exception: ForbiddenRequestException): ResponseEntity<Any?> {

        return buildResponseEntity(exception)
    }

    @ExceptionHandler(Exception::class)
    fun handleDefaultException(exception: Exception): ResponseEntity<Any?> {

        exception.printStackTrace()
        val internalServerException = InternalServerErrorException()
        return buildResponseEntity(internalServerException)
    }
}