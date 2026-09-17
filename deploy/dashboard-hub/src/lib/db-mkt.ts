import postgres from 'postgres';

/**
 * Segundo banco: o Supabase onde vivem os eventos dos sites (gnhorizons.com e
 * kasteller.com.py). O `sql` de `@/lib/db` continua sendo o banco do portal —
 * este aqui é só leitura do schema `hub`, com o papel `hub_reader`.
 *
 * Por que dois clientes e não um: são dois Postgres diferentes. Copiar os dados
 * para cá daria um job para manter e números atrasados; ler direto custa uma
 * conexão e mostra o site de agora.
 *
 * `prepare: false` é obrigatório: o pooler do Supabase roda em modo transação e
 * não guarda prepared statements entre uma consulta e outra.
 */
export const sqlMkt = postgres(process.env.MKT_DATABASE_URL!, {
  ssl: 'require',
  max: 3,
  idle_timeout: 20,
  connect_timeout: 10,
  prepare: false,
});
