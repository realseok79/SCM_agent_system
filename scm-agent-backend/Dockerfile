# Build stage
FROM gradle:8.7-jdk17 AS build
WORKDIR /app
COPY --chown=gradle:gradle . .
RUN gradle build --no-daemon -x test

# Package stage
FROM eclipse-temurin:17-jre-alpine
WORKDIR /app
COPY --from=build /app/build/libs/scm-agent-backend-0.0.1-SNAPSHOT.jar app.jar
EXPOSE 8080
ENTRYPOINT ["java", "-jar", "app.jar"]
