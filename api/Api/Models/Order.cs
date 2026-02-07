namespace Api.Models;

public record Order(
    Guid Id,
    string CustomerName,
    string Product,
    int Quantity,
    decimal? Price,
    string Status,
    string? EnrichmentData,
    DateTime CreatedAt,
    DateTime UpdatedAt
);

public record CreateOrderRequest(
    string CustomerName,
    string Product,
    int Quantity
);
