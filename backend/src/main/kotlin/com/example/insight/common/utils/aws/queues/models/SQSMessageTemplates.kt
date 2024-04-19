package com.example.insight.common.utils.aws.queues.models

data class SQSSendSingleMessageTemplate (
    val message: String ,
    val queueName: String,
    val delayInSeconds: Int? = 0
)

data class SQSSendBatchMessageTemplate (
    val message: List<String>,
    val batchSize: Int = 10,
    val queueName: String,
    val delayInSeconds: Int = 0
)