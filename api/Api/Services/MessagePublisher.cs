using System.Text;
using System.Text.Json;
using RabbitMQ.Client;

namespace Api.Services;

public class MessagePublisher : IAsyncDisposable
{
    private readonly IConfiguration _config;
    private readonly ILogger<MessagePublisher> _logger;
    private IConnection? _connection;
    private IChannel? _channel;
    private bool _exchangeDeclared;
    private readonly SemaphoreSlim _lock = new(1, 1);

    public MessagePublisher(IConfiguration config, ILogger<MessagePublisher> logger)
    {
        _config = config;
        _logger = logger;
    }

    private async Task<IChannel> GetChannelAsync()
    {
        if (_channel is not null) return _channel;

        await _lock.WaitAsync();
        try
        {
            if (_channel is not null) return _channel;

            var factory = new ConnectionFactory
            {
                HostName = _config["RabbitMQ:Host"] ?? "localhost",
                UserName = _config["RabbitMQ:Username"] ?? "demo",
                Password = _config["RabbitMQ:Password"] ?? "demo"
            };
            _connection = await factory.CreateConnectionAsync();
            _channel = await _connection.CreateChannelAsync();
            return _channel;
        }
        finally
        {
            _lock.Release();
        }
    }

    public async Task PublishOrderCreatedAsync(object order)
    {
        var channel = await GetChannelAsync();

        if (!_exchangeDeclared)
        {
            await channel.ExchangeDeclareAsync("orders", ExchangeType.Topic, durable: true);
            _exchangeDeclared = true;
        }

        var body = Encoding.UTF8.GetBytes(JsonSerializer.Serialize(order));
        var props = new BasicProperties { ContentType = "application/json" };
        await channel.BasicPublishAsync("orders", "order.created", false, props, body);
        _logger.LogInformation("Published order.created event");
    }

    public async ValueTask DisposeAsync()
    {
        if (_channel is not null) await _channel.CloseAsync();
        if (_connection is not null) await _connection.CloseAsync();
    }
}
