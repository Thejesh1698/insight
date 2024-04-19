package com.example.insight.common.models.entities

import org.springframework.jdbc.core.RowMapper
import java.sql.ResultSet

data class Reaction(
    val reactionId: Long,
    val reaction: String
)

class ReactionRowMapper : RowMapper<Reaction> {

    override fun mapRow(rs: ResultSet, rowNum: Int): Reaction {
        return Reaction(
            reactionId = rs.getLong("reaction_id"),
            reaction = rs.getString("reaction")
        )
    }
}