using Api.Models;
using Dapper;
using Npgsql;

namespace Api.Services;

public class OrderRepository(IConfiguration config)
{
    private const string Columns = """
        id AS Id,
        customer_name AS CustomerName,
        product AS Product,
        quantity AS Quantity,
        price AS Price,
        status AS Status,
        enrichment_data AS EnrichmentData,
        created_at AS CreatedAt,
        updated_at AS UpdatedAt
        """;

    private NpgsqlConnection CreateConnection() =>
        new(config.GetConnectionString("Postgres"));

    public async Task<Order> CreateAsync(CreateOrderRequest request, decimal? price, string? enrichmentData)
    {
        await using var conn = CreateConnection();
        var sql = $"""
            INSERT INTO orders (customer_name, product, quantity, price, enrichment_data)
            VALUES (@CustomerName, @Product, @Quantity, @Price, @EnrichmentData::jsonb)
            RETURNING {Columns};
            """;

        return await conn.QuerySingleAsync<Order>(sql, new
        {
            request.CustomerName,
            request.Product,
            request.Quantity,
            Price = price,
            EnrichmentData = enrichmentData
        });
    }

    public async Task<IEnumerable<Order>> GetAllAsync()
    {
        await using var conn = CreateConnection();
        return await conn.QueryAsync<Order>(
            $"SELECT {Columns} FROM orders ORDER BY created_at DESC");
    }

    public async Task<Order?> GetByIdAsync(Guid id)
    {
        await using var conn = CreateConnection();
        return await conn.QuerySingleOrDefaultAsync<Order>(
            $"SELECT {Columns} FROM orders WHERE id = @Id",
            new { Id = id });
    }
}
