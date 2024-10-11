package com.example.insight.common.utils.aws.queues.services

import com.amazonaws.services.sqs.model.*
import com.example.insight.common.errorHandler.exceptions.InternalServerErrorException
import com.example.insight.common.utils.aws.queues.AmazonSqsClient
import com.example.insight.common.utils.aws.queues.AmazonSqsManager
import com.example.insight.common.utils.aws.queues.models.SQSSendBatchMessageTemplate
import com.example.insight.common.utils.aws.queues.models.SQSSendSingleMessageTemplate
import org.slf4j.Logger
import org.slf4j.LoggerFactory
import org.springframework.beans.factory.annotation.Autowired
import org.springframework.stereotype.Service

/** This service is currently implementing methods for standard queues only.  **/
@Service
class AmazonSqsStandardQueueService : AmazonSqsManager {

    @Autowired
    private lateinit var sqsClient: AmazonSqsClient

    private val logger: Logger = LoggerFactory.getLogger(this.javaClass)

    override fun sendMessage(messageTemplate: SQSSendSingleMessageTemplate) {

        sendSingleMessage(messageTemplate)
    }

    override fun sendBatchMessage(messageTemplate: SQSSendBatchMessageTemplate) {

        if(messageTemplate.batchSize > 10) {
            val errorMessage = "batch size cannot exceed 10"
            logger.error("$errorMessage --- messageTemplate: $messageTemplate")
            throw InternalServerErrorException()
        }

        // Creating a batch of 10 messages(SQS max limit) and sending on SQS
        val messageChunks = messageTemplate.message.chunked(messageTemplate.batchSize)
        for (chunks in messageChunks) {
            val batchRequest = createMessageRequest(chunks, delayInSeconds = messageTemplate.delayInSeconds)
            if (batchRequest != null) {
                sendBatchMessage(queueName = messageTemplate.queueName, Entries = batchRequest)
            }
        }
    }

    override fun getMessage() {
        return
    }

    private fun getQueueUrl(queueName: String): String? {
        return try {
            sqsClient.getQueueUrl(queueName)
        } catch (e: AmazonSQSException) {
            logger.error("Error while getting queue URL. Please check queue name. " +
                    "--- exception: ${e.message} | ${e.errorType}")
            throw InternalServerErrorException()
        }
    }

    private fun createMessageRequest(messages: List<Any>, delayInSeconds: Int)
            : MutableList<SendMessageBatchRequestEntry>? {

        return try {
            val batchMessages: MutableList<SendMessageBatchRequestEntry> = arrayListOf()
            for ((itr, message) in messages.withIndex()) {
                batchMessages.add(
                    SendMessageBatchRequestEntry()
                        .withId(itr.toString())
                        .withMessageBody(message.toString())
                        .withDelaySeconds(delayInSeconds)
                )
            }
            batchMessages
        } catch (e: AmazonSQSException) {
            logger.error("Error while creating the batch request --- exception: ${e.message} | ${e.errorType}")
            throw InternalServerErrorException()
        }
    }

    private fun sendSingleMessage(messageTemplate: SQSSendSingleMessageTemplate): SendMessageResult? {

        return try {
            val queueUrl = getQueueUrl(messageTemplate.queueName)
            val sendMessageRequest = SendMessageRequest()
                .withQueueUrl(queueUrl)
                .withMessageBody(messageTemplate.message)
                .withDelaySeconds(messageTemplate.delayInSeconds)
            sqsClient.sendMessage(sendMessageRequest)
        } catch (e: AmazonSQSException) {
            logger.error("Error while sending single message on SQS --- exception: ${e.message} | ${e.errorType}")
            throw InternalServerErrorException()
        }
    }

    private fun sendBatchMessage(queueName: String, Entries: Collection<SendMessageBatchRequestEntry>)
            : SendMessageBatchResult? {

        return try {
            val queueUrl = getQueueUrl(queueName)
            val sendMessageBatchRequest = SendMessageBatchRequest()
                .withQueueUrl(queueUrl)
                .withEntries(Entries)
            sqsClient.sendBatchMessages(sendMessageBatchRequest)
        } catch (e: AmazonSQSException) {
            logger.error("Error while sending batch messages on SQS --- exception: ${e.message} | ${e.errorType}")
            throw InternalServerErrorException()
        }
    }
}