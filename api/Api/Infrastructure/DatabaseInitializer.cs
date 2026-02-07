using Npgsql;

namespace Api.Infrastructure;

public class DatabaseInitializer(IConfiguration config, ILogger<DatabaseInitializer> logger)
    : BackgroundService
{
    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        var connectionString = config.GetConnectionString("Postgres");
        const string sql = """
            CREATE TABLE IF NOT EXISTS orders (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                customer_name VARCHAR(200) NOT NULL,
                product VARCHAR(200) NOT NULL,
                quantity INT NOT NULL,
                price DECIMAL(10,2),
                status VARCHAR(50) NOT NULL DEFAULT 'pending',
                enrichment_data JSONB,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            """;

        for (var attempt = 1; attempt <= 10; attempt++)
        {
            try
            {
                await using var conn = new NpgsqlConnection(connectionString);
                await conn.OpenAsync(stoppingToken);
                await using var cmd = new NpgsqlCommand(sql, conn);
                await cmd.ExecuteNonQueryAsync(stoppingToken);
                logger.LogInformation("Database initialized successfully");
                return;
            }
            catch (Exception ex) when (attempt < 10)
            {
                logger.LogWarning(ex, "Database init attempt {Attempt} failed, retrying...", attempt);
                await Task.Delay(TimeSpan.FromSeconds(2), stoppingToken);
            }
        }
    }
}
