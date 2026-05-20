package com.sigma.scm.repository;

import com.sigma.scm.domain.RegionalInsight;
import com.sigma.scm.domain.RegionalInsightId;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface RegionalInsightRepository extends JpaRepository<RegionalInsight, RegionalInsightId> {
    List<RegionalInsight> findByIdRegionCode(String regionCode);
}
