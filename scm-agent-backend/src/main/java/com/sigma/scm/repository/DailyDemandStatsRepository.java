package com.sigma.scm.repository;

import com.sigma.scm.domain.DailyDemandStats;
import com.sigma.scm.domain.DailyDemandStatsId;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface DailyDemandStatsRepository extends JpaRepository<DailyDemandStats, DailyDemandStatsId> {
    List<DailyDemandStats> findByIdRegionCode(String regionCode);
}
