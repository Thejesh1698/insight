package com.example.insight.common.configurations

import org.springframework.beans.factory.annotation.Qualifier
import org.springframework.boot.autoconfigure.jdbc.DataSourceProperties
import org.springframework.boot.context.properties.ConfigurationProperties
import org.springframework.context.annotation.Bean
import org.springframework.context.annotation.Configuration
import org.springframework.jdbc.core.JdbcTemplate
import org.springframework.jdbc.datasource.DataSourceTransactionManager
import org.springframework.transaction.PlatformTransactionManager
import javax.sql.DataSource


@Configuration
class MLDataSourceConfiguration {
    @Bean
    @ConfigurationProperties("spring.datasource.ml")
    fun mlDataSourceProperties(): DataSourceProperties {
        return DataSourceProperties()
    }

    @Bean
    fun mlDataSource(): DataSource {
        return mlDataSourceProperties()
            .initializeDataSourceBuilder()
            .build()
    }

    @Bean
    fun mlDatabaseJdbcTemplate(@Qualifier("mlDataSource") dataSource: DataSource): JdbcTemplate {
        return JdbcTemplate(dataSource)
    }

    @Bean(name = ["mlDatabaseTransactionManager"])
    fun mlDatabaseTransactionManager(@Qualifier("mlDataSource") dataSource: DataSource): PlatformTransactionManager {
        return DataSourceTransactionManager(dataSource)
    }
}