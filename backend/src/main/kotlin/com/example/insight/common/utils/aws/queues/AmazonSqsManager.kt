package com.example.insight.common.utils.aws.queues

import com.example.insight.common.utils.aws.queues.models.SQSSendBatchMessageTemplate
import com.example.insight.common.utils.aws.queues.models.SQSSendSingleMessageTemplate

/** This interface defines basic methods to be defined for all type of queues. **/
interface AmazonSqsManager {

    fun sendMessage (messageTemplate: SQSSendSingleMessageTemplate){ }

    fun sendBatchMessage(messageTemplate: SQSSendBatchMessageTemplate){}

    fun getMessage(){}

}