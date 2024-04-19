package com.example.insight.common.utils.aws.parameterStore

import com.amazonaws.auth.AWSCredentials
import com.amazonaws.auth.AWSStaticCredentialsProvider
import com.amazonaws.auth.BasicAWSCredentials
import com.amazonaws.regions.Regions
import com.amazonaws.services.simplesystemsmanagement.AWSSimpleSystemsManagement
import com.amazonaws.services.simplesystemsmanagement.AWSSimpleSystemsManagementClientBuilder
import com.amazonaws.services.simplesystemsmanagement.model.*
import com.example.insight.common.utils.aws.properties.AwsProperties
import jakarta.annotation.PostConstruct
import org.slf4j.Logger
import org.slf4j.LoggerFactory
import org.springframework.stereotype.Service

@Service
class AmazonSsmClient(val awsProperties: AwsProperties) {

    private lateinit var smsClient: AWSSimpleSystemsManagement

    private val logger: Logger = LoggerFactory.getLogger(this.javaClass)

    @PostConstruct
    private fun initializeAmazonSqsClient() {
        try {
            val credentials: AWSCredentials =
                BasicAWSCredentials(awsProperties.authentication.accessKey, awsProperties.authentication.secretKey)
            smsClient = AWSSimpleSystemsManagementClientBuilder
                .standard()
                .withRegion(Regions.fromName(awsProperties.sqs.region))
                .withCredentials(AWSStaticCredentialsProvider(credentials))
                .build()
        } catch (exception: Exception) {
            logger.error("Error while initializing AWSSqsClient exception: ${exception.message}")
        }
    }

    fun getParam(parameterRequest: GetParameterRequest)
            : GetParameterResult? {

        return smsClient.getParameter(parameterRequest)
    }

    fun updateParam(parameterRequest: PutParameterRequest)
            : PutParameterResult? {

        return smsClient.putParameter(parameterRequest)
    }
}