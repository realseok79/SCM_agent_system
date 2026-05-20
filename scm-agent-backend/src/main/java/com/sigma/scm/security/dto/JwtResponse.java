package com.sigma.scm.security.dto;

public record JwtResponse(
    String accessToken,
    String refreshToken,
    String tokenType,
    long expiresIn,
    String role
) {
    public JwtResponse(String accessToken, String refreshToken, long expiresIn, String role) {
        this(accessToken, refreshToken, "Bearer", expiresIn, role);
    }
}
