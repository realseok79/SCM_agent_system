package com.sigma.scm.domain;

import jakarta.persistence.Column;
import jakarta.persistence.EmbeddedId;
import jakarta.persistence.Entity;
import jakarta.persistence.Table;
import lombok.Data;
import lombok.NoArgsConstructor;

@Entity
@Table(name = "daily_demand_stats")
@Data
@NoArgsConstructor
public class DailyDemandStats {

    @EmbeddedId
    private DailyDemandStatsId id;

    @Column(name = "daily_outbound_total", nullable = false)
    private Double dailyOutboundTotal = 0.0;

    @Column(name = "moving_avg_30d", nullable = false)
    private Double movingAvg30d = 0.0;
}
