using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Logging;
using OWTWeb.OWTDB.Entities;
using System.Collections.Generic;
using System.Linq;

namespace OWTWeb.OWTDB.Api
{
    public class LiteralTranslations
    {
        public string LanguageIso { get; set; }
        public string Translation { get; set; }
    }

    public class Literals(DbContext dbconn, ILogger<Literals> logger) : ApiBase(dbconn, logger)
    {
        // Create a new literal with translations
        public async Task<int> CreateTranslationAsync(string key, string tags, IList<LiteralTranslations> translations)
        {
            DbSet<Literal> literals = dbconn.Set<Literal>();
            var literal = new Literal { Name = key, Tags = tags };
            literals.Add(literal);
            await dbconn.SaveChangesAsync();

            DbSet<Literaltranslation> literalTranslations = dbconn.Set<Literaltranslation>();
            foreach (var translation in translations)
            {
                literalTranslations.Add(new Literaltranslation
                {
                    IdLiteral = literal.IdLiteral,
                    LanguageIso = translation.LanguageIso,
                    Translation = translation.Translation
                });
            }
            return await dbconn.SaveChangesAsync();
        }

        // Update an existing translation by language ISO and key
        public async Task<int> UpdateTranslationAsync(string languageIso, string key, string translation)
        {
            DbSet<Literal> literals = dbconn.Set<Literal>();
            var literal = await literals.FirstOrDefaultAsync(l => l.Name == key);
            if (literal == null) return 0;

            DbSet<Literaltranslation> literalTranslations = dbconn.Set<Literaltranslation>();
            var existing = await literalTranslations
                .FirstOrDefaultAsync(t => t.IdLiteral == literal.IdLiteral && t.LanguageIso == languageIso);

            if (existing != null)
            {
                existing.Translation = translation;
                dbconn.Entry(existing).State = EntityState.Modified;
            }
            else
            {
                literalTranslations.Add(new Literaltranslation
                {
                    IdLiteral = literal.IdLiteral,
                    LanguageIso = languageIso,
                    Translation = translation
                });
            }
            return await dbconn.SaveChangesAsync();
        }

        // Remove a literal and all its translations by key
        public async Task<int> RemoveKeyAsync(string key)
        {
            DbSet<Literal> literals = dbconn.Set<Literal>();
            var literal = await literals.FirstOrDefaultAsync(l => l.Name == key);
            if (literal == null) return 0;

            DbSet<Literaltranslation> literalTranslations = dbconn.Set<Literaltranslation>();
            var translations = await literalTranslations
                .Where(t => t.IdLiteral == literal.IdLiteral)
                .ToListAsync();

            literalTranslations.RemoveRange(translations);
            literals.Remove(literal);
            return await dbconn.SaveChangesAsync();
        }

        // Get all translations for a given language ISO and optional tags filter
        public async Task<IList<object>> GetTranslationsAsync(string languageIso, string tags = null)
        {
            DbSet<Literal> literals = dbconn.Set<Literal>();
            DbSet<Literaltranslation> literalTranslations = dbconn.Set<Literaltranslation>();

            var query = literals.AsQueryable();

            if (!string.IsNullOrEmpty(tags))
            {
                var tagList = tags.Split(',').Select(t => t.Trim().ToLower()).ToList();
                query = query.Where(l => tagList.All(tag => l.Tags != null && l.Tags.Contains(tag)));
            }

            var result = await query
                .Join(literalTranslations,
                    l => l.IdLiteral,
                    t => t.IdLiteral,
                    (l, t) => new { l.Name, t.LanguageIso, t.Translation })
                .Where(x => x.LanguageIso == languageIso)
                .Select(x => (object)new { key = x.Name, translation = x.Translation })
                .ToListAsync();

            return result;
        }
    }
}