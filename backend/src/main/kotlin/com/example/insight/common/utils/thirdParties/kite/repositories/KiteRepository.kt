package com.example.insight.common.utils.thirdParties.kite.repositories

import com.fasterxml.jackson.databind.ObjectMapper
import com.fasterxml.jackson.module.kotlin.KotlinModule
import com.example.insight.common.utils.aws.parameterStore.services.AwsParameterStoreService
import com.example.insight.common.utils.aws.parameterStore.utils.ParameterStoreConstants
import com.example.insight.common.utils.thirdParties.kite.models.KiteTokens
import org.springframework.beans.factory.annotation.Autowired
import org.springframework.stereotype.Service

@Service
class KiteRepository {

    val objectMapper: ObjectMapper = ObjectMapper().registerModule(KotlinModule())

    @Autowired
    lateinit var awsParameterStoreService: AwsParameterStoreService

    fun getKiteTokens(): KiteTokens {

        val value = awsParameterStoreService.getParam(ParameterStoreConstants.ParameterKeys.KITE_TOKENS)
        return objectMapper.readValue(
            value, KiteTokens::class.java
        )
    }

    fun updateKiteTokens(tokens: KiteTokens) {

        awsParameterStoreService.updateParam(
            ParameterStoreConstants.ParameterKeys.KITE_TOKENS, objectMapper.writeValueAsString(tokens), true
        )
    }
}