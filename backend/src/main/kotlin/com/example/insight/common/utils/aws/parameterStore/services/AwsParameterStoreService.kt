package com.example.insight.common.utils.aws.parameterStore.services

import com.amazonaws.services.simplesystemsmanagement.model.GetParameterRequest
import com.amazonaws.services.simplesystemsmanagement.model.PutParameterRequest
import com.example.insight.common.utils.aws.parameterStore.AmazonSsmClient
import com.example.insight.common.utils.aws.parameterStore.utils.ParameterStoreConstants
import org.springframework.beans.factory.annotation.Autowired
import org.springframework.stereotype.Service


@Service
class AwsParameterStoreService {

    @Autowired
    lateinit var amazonSsmClient: AmazonSsmClient

    fun getParam(paramKey: ParameterStoreConstants.ParameterKeys): String? {

        val paramRequest = GetParameterRequest().apply {
            name = paramKey.value
        }
        return amazonSsmClient.getParam(paramRequest)?.parameter?.value
    }

    fun updateParam(paramKey: ParameterStoreConstants.ParameterKeys, paramValue: String, overwrite: Boolean) {

        val paramRequest = PutParameterRequest().apply {
            name = paramKey.value
            value = paramValue
            this.isOverwrite = overwrite
        }
        amazonSsmClient.updateParam(paramRequest)
    }
}