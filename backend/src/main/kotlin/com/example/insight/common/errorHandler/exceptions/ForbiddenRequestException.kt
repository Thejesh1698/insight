package com.example.insight.common.errorHandler.exceptions

import com.example.insight.common.constants.ApiMessages
import com.example.insight.common.errorHandler.ErrorTypes
import org.springframework.http.HttpStatus


class ForbiddenRequestException(
    override val errorType: Any = ErrorTypes.Http4xxErrors.Authentication.FORBIDDEN_REQUEST,
    override var message: String = ApiMessages.Common.error403,
    override val notifyUser: Boolean = true,
    override var httpStatus: HttpStatus = HttpStatus.FORBIDDEN
) : CustomException()