package com.sigma.scm.domain;

import jakarta.persistence.*;
import lombok.Data;
import lombok.NoArgsConstructor;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;
import java.time.LocalDateTime;

@Entity
@Table(name = "ml_inference_logs")
@Data
@NoArgsConstructor
public class MlInferenceLog {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "inference_id")
    private Long inferenceId;

    @Column(name = "product_name", nullable = false, length = 100)
    private String productName;

    @Column(name = "region_code", nullable = false, length = 50)
    private String regionCode;

    @Column(name = "target_date", nullable = false, length = 20)
    private String targetDate;

    @Column(name = "predicted_demand_10", nullable = false)
    private Double predictedDemand10;

    @Column(name = "predicted_demand_50", nullable = false)
    private Double predictedDemand50;

    @Column(name = "predicted_demand_90", nullable = false)
    private Double predictedDemand90;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "shap_values", nullable = false, columnDefinition = "jsonb")
    private String shapValues = "{}";

    @Column(name = "model_version", nullable = false, length = 100)
    private String modelVersion;

    @Column(name = "created_at")
    private LocalDateTime createdAt = LocalDateTime.now();
}
