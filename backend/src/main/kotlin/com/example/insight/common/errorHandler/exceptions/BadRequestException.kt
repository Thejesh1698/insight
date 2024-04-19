package com.example.insight.common.errorHandler.exceptions

import com.example.insight.common.constants.ApiMessages
import com.example.insight.common.errorHandler.ErrorTypes
import org.springframework.http.HttpStatus

class BadRequestException(
    override val errorType: Any = ErrorTypes.Http4xxErrors.BAD_REQUEST,
    override var message: String = ApiMessages.Common.error400,
    override val notifyUser: Boolean = true,
    override var httpStatus: HttpStatus = HttpStatus.BAD_REQUEST
) : CustomException()