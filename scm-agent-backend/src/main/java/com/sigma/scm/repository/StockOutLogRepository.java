package com.sigma.scm.repository;

import com.sigma.scm.domain.StockOutLog;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface StockOutLogRepository extends JpaRepository<StockOutLog, Long> {
    List<StockOutLog> findByRegionCode(String regionCode);
}
