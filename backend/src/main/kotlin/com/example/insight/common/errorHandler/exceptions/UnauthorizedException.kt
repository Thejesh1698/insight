package com.example.insight.common.errorHandler.exceptions

import com.example.insight.common.constants.ApiMessages
import com.example.insight.common.errorHandler.ErrorTypes
import org.springframework.http.HttpStatus
import org.springframework.web.bind.annotation.ResponseStatus

@ResponseStatus(value = HttpStatus.UNAUTHORIZED, reason = ApiMessages.Common.error401)
class UnauthorizedException(
    override val errorType: Any = ErrorTypes.Http4xxErrors.Authentication.NOT_AUTHORIZED,
    override var message: String = ApiMessages.Common.error401,
    override val notifyUser: Boolean = true,
    override var httpStatus: HttpStatus = HttpStatus.UNAUTHORIZED
) : CustomException()