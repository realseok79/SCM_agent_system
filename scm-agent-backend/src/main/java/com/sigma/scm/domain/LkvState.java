package com.sigma.scm.domain;

import jakarta.persistence.Column;
import jakarta.persistence.EmbeddedId;
import jakarta.persistence.Entity;
import jakarta.persistence.Table;
import lombok.Data;
import lombok.NoArgsConstructor;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

import java.time.LocalDateTime;

@Entity
@Table(name = "lkv_state")
@Data
@NoArgsConstructor
public class LkvState {

    @EmbeddedId
    private LkvStateId id;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "state_data", nullable = false, columnDefinition = "jsonb")
    private String stateData = "{}";

    @Column(name = "updated_at")
    private LocalDateTime updatedAt = LocalDateTime.now();
}
