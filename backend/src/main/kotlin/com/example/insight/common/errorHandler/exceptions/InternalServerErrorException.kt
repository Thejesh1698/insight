package com.example.insight.common.errorHandler.exceptions

import com.example.insight.common.constants.ApiMessages
import com.example.insight.common.errorHandler.ErrorTypes
import org.springframework.http.HttpStatus

class InternalServerErrorException(
    override val errorType: Any = ErrorTypes.Http5xxErrors.INTERNAL_SERVER_ERROR,
    override var message: String = ApiMessages.Common.error500,
    override val notifyUser: Boolean = true,
    override var httpStatus: HttpStatus = HttpStatus.INTERNAL_SERVER_ERROR
) : CustomException()