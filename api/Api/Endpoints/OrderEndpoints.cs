using System.Diagnostics;
using Api.Models;
using Api.Services;

namespace Api.Endpoints;

public static class OrderEndpoints
{
    public static void MapOrderEndpoints(this WebApplication app)
    {
        var group = app.MapGroup("/orders");

        group.MapPost("/", async (
            CreateOrderRequest request,
            OrderRepository repo,
            EnrichmentClient enrichment,
            MessagePublisher publisher,
            OrderMetrics metrics) =>
        {
            Activity.Current?.SetTag("order.product", request.Product);
            Activity.Current?.SetTag("order.quantity", request.Quantity);

            if (string.IsNullOrWhiteSpace(request.CustomerName) || string.IsNullOrWhiteSpace(request.Product) || request.Quantity <= 0)
            {
                metrics.RecordOrderError(request.Product, "validation_error");
                return Results.BadRequest(new { error = "CustomerName, Product, and Quantity (> 0) are required." });
            }

            if (request.Product.Equals("error", StringComparison.OrdinalIgnoreCase))
            {
                Activity.Current?.SetStatus(ActivityStatusCode.Error, "Simulated error for product 'error'");
                Activity.Current?.AddEvent(new ActivityEvent("error.simulated"));
                metrics.RecordOrderError(request.Product, "simulated_error");
                throw new InvalidOperationException("Simulated error: product 'error' triggers failure");
            }

            var (price, rawJson) = await enrichment.EnrichAsync(request.Product, request.Quantity);

            var order = await repo.CreateAsync(request, price, rawJson);

            await publisher.PublishOrderCreatedAsync(new { order.Id, order.Product, order.Quantity, order.Price });

            // Record successful order creation metric
            metrics.RecordOrderCreated(order.Product, order.Quantity);

            return Results.Created($"/orders/{order.Id}", order);
        });

        group.MapGet("/", async (OrderRepository repo) =>
        {
            var orders = await repo.GetAllAsync();
            return Results.Ok(orders);
        });

        group.MapGet("/{id:guid}", async (Guid id, OrderRepository repo) =>
        {
            var order = await repo.GetByIdAsync(id);
            return order is not null ? Results.Ok(order) : Results.NotFound();
        });
    }
}
