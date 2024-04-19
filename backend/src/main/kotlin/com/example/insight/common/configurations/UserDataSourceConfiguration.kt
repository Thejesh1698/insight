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
class UserDataSourceConfiguration {
    @Bean
    @ConfigurationProperties("spring.datasource.user")
    fun userDataSourceProperties(): DataSourceProperties {
        return DataSourceProperties()
    }

    @Bean
    @ConfigurationProperties("spring.datasource.user.hikari")
    fun userDataSource(): DataSource {
        return userDataSourceProperties()
            .initializeDataSourceBuilder()
            .build()
    }

    @Bean
    fun userDatabaseJdbcTemplate(@Qualifier("userDataSource") dataSource: DataSource): JdbcTemplate {
        return JdbcTemplate(dataSource)
    }

    @Bean(name = ["userDatabaseTransactionManager"])
    fun userDatabaseTransactionManager(@Qualifier("userDataSource") dataSource: DataSource): PlatformTransactionManager {
        return DataSourceTransactionManager(dataSource)
    }
}