package com.example.insight.common.utils.aws.queues

import com.amazonaws.auth.AWSCredentials
import com.amazonaws.auth.AWSStaticCredentialsProvider
import com.amazonaws.auth.BasicAWSCredentials
import com.amazonaws.regions.Regions
import com.amazonaws.services.sqs.AmazonSQSAsync
import com.amazonaws.services.sqs.AmazonSQSAsyncClientBuilder
import com.amazonaws.services.sqs.model.*
import com.example.insight.common.utils.aws.properties.AwsProperties
import jakarta.annotation.PostConstruct
import org.slf4j.Logger
import org.slf4j.LoggerFactory
import org.springframework.stereotype.Service

@Service
class AmazonSqsClient(val awsProperties: AwsProperties) {

    private lateinit var sqsClient: AmazonSQSAsync

    private val logger: Logger = LoggerFactory.getLogger(this.javaClass)

    @PostConstruct
    private fun initializeAmazonSqsClient() {
        try {
            val credentials: AWSCredentials =
                BasicAWSCredentials(awsProperties.authentication.accessKey, awsProperties.authentication.secretKey)
            sqsClient = AmazonSQSAsyncClientBuilder
                .standard()
                .withRegion(Regions.fromName(awsProperties.sqs.region))
                .withCredentials(AWSStaticCredentialsProvider(credentials))
                .build()
        } catch (exception: Exception) {
            logger.error("Error while initializing AWSSqsClient exception: ${exception.message}")
        }
    }

    fun sendMessage(sendMessageRequest: SendMessageRequest)
            : SendMessageResult? {

        return sqsClient.sendMessage(sendMessageRequest)
    }

    fun sendBatchMessages(sendMessageBatchRequest: SendMessageBatchRequest)
            : SendMessageBatchResult? {

        return sqsClient.sendMessageBatch(sendMessageBatchRequest)
    }

    fun getQueueUrl(queueName: String): String? {

        return sqsClient.getQueueUrl(queueName).queueUrl
    }
}