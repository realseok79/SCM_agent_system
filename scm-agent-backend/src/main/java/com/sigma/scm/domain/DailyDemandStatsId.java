package com.sigma.scm.domain;

import jakarta.persistence.Embeddable;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;

@Embeddable
@Data
@NoArgsConstructor
@AllArgsConstructor
public class DailyDemandStatsId implements Serializable {
    private String regionCode;
    private String productName;
    private String date;
}
