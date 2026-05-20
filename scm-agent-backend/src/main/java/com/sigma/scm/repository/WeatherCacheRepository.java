package com.sigma.scm.repository;

import com.sigma.scm.domain.WeatherCache;
import com.sigma.scm.domain.WeatherCacheId;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface WeatherCacheRepository extends JpaRepository<WeatherCache, WeatherCacheId> {
    List<WeatherCache> findByIdRegionCode(String regionCode);
}
