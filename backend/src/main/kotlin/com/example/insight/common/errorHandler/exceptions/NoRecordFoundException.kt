package com.example.insight.common.errorHandler.exceptions

import com.example.insight.common.constants.ApiMessages
import com.example.insight.common.errorHandler.ErrorTypes
import org.springframework.http.HttpStatus

class NoRecordFoundException(
    override val errorType: Any = ErrorTypes.Http4xxErrors.NOT_FOUND,
    override var message: String = ApiMessages.Common.error404,
    override val notifyUser: Boolean = true,
    override var httpStatus: HttpStatus = HttpStatus.NOT_FOUND
) : CustomException()