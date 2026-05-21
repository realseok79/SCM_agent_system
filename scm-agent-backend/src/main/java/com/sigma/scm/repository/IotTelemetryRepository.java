package com.sigma.scm.repository;

import com.sigma.scm.domain.IotTelemetry;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface IotTelemetryRepository extends JpaRepository<IotTelemetry, Long> {
    List<IotTelemetry> findByDeviceId(String deviceId);
}
