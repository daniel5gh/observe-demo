using System.Text.Json;

namespace Api.Services;

public class EnrichmentClient(HttpClient http, ILogger<EnrichmentClient> logger)
{
    public async Task<(decimal? Price, string? RawJson)> EnrichAsync(string product, int quantity)
    {
        try
        {
            var response = await http.PostAsJsonAsync("/enrich", new { product, quantity });
            response.EnsureSuccessStatusCode();
            var json = await response.Content.ReadAsStringAsync();
            var doc = JsonDocument.Parse(json);
            var price = doc.RootElement.TryGetProperty("price", out var p) ? p.GetDecimal() : (decimal?)null;
            return (price, json);
        }
        catch (Exception ex)
        {
            logger.LogWarning(ex, "Enrichment call failed for product {Product}", product);
            return (null, null);
        }
    }
}
