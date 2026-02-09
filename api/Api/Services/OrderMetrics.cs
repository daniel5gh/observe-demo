using System.Diagnostics.Metrics;

namespace Api.Services;

public class OrderMetrics
{
    private readonly Counter<long> _ordersCreatedCounter;
    private readonly Counter<long> _orderErrorsCounter;

    public OrderMetrics(IMeterFactory meterFactory)
    {
        var meter = meterFactory.Create("Api.Orders");

        _ordersCreatedCounter = meter.CreateCounter<long>(
            "orders.created",
            unit: "{order}",
            description: "Total number of orders created");

        _orderErrorsCounter = meter.CreateCounter<long>(
            "orders.errors",
            unit: "{error}",
            description: "Total number of order creation errors");
    }

    public void RecordOrderCreated(string product, int quantity)
    {
        _ordersCreatedCounter.Add(1,
            new KeyValuePair<string, object?>("product", product),
            new KeyValuePair<string, object?>("quantity", quantity));
    }

    public void RecordOrderError(string? product, string errorType)
    {
        _orderErrorsCounter.Add(1,
            new KeyValuePair<string, object?>("product", product ?? "unknown"),
            new KeyValuePair<string, object?>("error.type", errorType));
    }
}
