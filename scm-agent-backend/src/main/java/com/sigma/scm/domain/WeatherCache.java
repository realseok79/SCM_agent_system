package com.sigma.scm.domain;

import jakarta.persistence.Column;
import jakarta.persistence.EmbeddedId;
import jakarta.persistence.Entity;
import jakarta.persistence.Table;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

@Entity
@Table(name = "weather_cache")
@Data
@NoArgsConstructor
public class WeatherCache {

    @EmbeddedId
    private WeatherCacheId id;

    private Double temp;
    private Double humidity;
    private Double precipitation;

    @Column(name = "weather_desc", length = 255)
    private String weatherDesc;

    @Column(name = "updated_at")
    private LocalDateTime updatedAt = LocalDateTime.now();
}
