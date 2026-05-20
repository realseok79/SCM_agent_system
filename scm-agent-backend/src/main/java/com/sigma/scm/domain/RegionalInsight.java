package com.sigma.scm.domain;

import jakarta.persistence.Column;
import jakarta.persistence.EmbeddedId;
import jakarta.persistence.Entity;
import jakarta.persistence.Table;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

@Entity
@Table(name = "regional_insights")
@Data
@NoArgsConstructor
public class RegionalInsight {

    @EmbeddedId
    private RegionalInsightId id;

    @Column(name = "action_plan_msg", nullable = false, columnDefinition = "TEXT")
    private String actionPlanMsg;

    @Column(name = "updated_at")
    private LocalDateTime updatedAt = LocalDateTime.now();
}
