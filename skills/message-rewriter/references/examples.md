# Exemplos antes/depois (pt-BR)

Cada exemplo mostra o rascunho do usuário e a saída esperada. Use para calibrar tamanho e dose de cuidado.

Nenhuma saída usa um fato que não esteja no rascunho. O que falta (horário, link, nome, prazo, causa) vira `[marcador]`. Siga o mesmo padrão: se você precisar de um dado que o usuário não deu, não invente.

---

## Direto

### PR: sugestão de performance

Rascunho:
> essa query ta fazendo 3 chamadas no banco, ta lento, tem que refatorar isso com join

Saída:

**Intenção:** sugerir melhoria de performance · **Tom:** Direto · **Canal:** PR
```
suggestion: essa query faz 3 chamadas ao banco e está lenta. Dá pra unificar num JOIN?
```

### PR: nit

Rascunho:
> nome de variavel ruim, data não diz nada

Saída:

**Intenção:** nome pouco claro · **Tom:** Direto · **Canal:** PR
```
nitpick (non-blocking): `data` ficou genérico. Um nome que diga o conteúdo, como `[nomeDescritivo]`, deixaria mais claro.
```

### PR: bloqueante

Rascunho:
> isso aqui vai quebrar se o usuario não tiver empresa, vai dar undefined e estourar a tela inteira

Saída:

**Intenção:** apontar bug bloqueante · **Tom:** Direto · **Canal:** PR
```
issue (blocking): quando o usuário não tem empresa, `user.company` vem undefined e o acesso ao `.id` derruba a tela inteira. Precisa tratar esse caso antes do merge.
```

### Slack: pedir review

Rascunho:
> oi pessoal tudo bem? alguém consegue revisar meu pr? é pequeno

Saída:

**Intenção:** pedir review · **Tom:** Direto · **Canal:** Slack canal
```
Oi, pessoal! Alguém consegue revisar este PR? É pequeno: [link]
```

### Slack: bug em produção

Rascunho:
> gente o login com sso ta quebrado em prod, ta dando 500 pra todo mundo que usa google, vi no sentry

Saída:

**Intenção:** reportar incidente · **Tom:** Direto · **Canal:** Slack canal
```
Login via SSO Google está retornando 500 em produção para todos os usuários. Erro no Sentry: [link]. Alguém do [time responsável] consegue olhar?
```

---

## Colaborativo

### Discordar de abordagem no PR

Rascunho:
> não concordo com usar redux pra isso, é um estado local, ta complicando à toa

Saída:

**Intenção:** discordar da abordagem · **Tom:** Colaborativo · **Canal:** PR
```
question: esse estado parece local a [componente]. Tem algum consumidor fora dele que eu não vi? Se não tiver, um `useState` deixaria o fluxo mais simples que o Redux aqui.
```

### Cobrar prazo

Rascunho:
> e aí, cadê aquele endpoint? era pra ontem e eu to travado

Saída:

**Intenção:** cobrar entrega combinada · **Tom:** Colaborativo · **Canal:** Slack DM
```
Oi, [nome]! Sobre o endpoint de [X] que a gente combinou pra ontem: tô travado no front esperando ele. Consegue me passar uma previsão?
```

### Dizer não

Rascunho:
> não vou conseguir pegar isso essa sprint, to cheio

Saída:

**Intenção:** recusar demanda · **Tom:** Colaborativo · **Canal:** Slack DM
```
Essa sprint não consigo pegar: já estou com [demandas atuais]. Consigo olhar a partir de [quando].
```

### Apontar erro de alguém (canal público)

Rascunho:
> o fulano subiu sem rodar a migration e quebrou o checkout de novo

Saída:

**Intenção:** apontar falha no deploy · **Tom:** Colaborativo · **Canal:** Slack canal
```
O deploy de [horário] subiu sem a migration `[nome]` e o checkout quebrou. [Status atual.] Que tal incluir a migration no checklist de release pra não repetir?
```
**Nota:** o nome da pessoa e o "de novo" saíram de propósito. Se for um padrão, vale conversar com ela em DM.

---

## CNV completa

### Feedback de comportamento (DM)

Rascunho:
> toda vez que eu abro pr o ciclano demora uma semana pra revisar e ainda reclama de coisa que não tem nada a ver, to de saco cheio

Saída:

**Intenção:** feedback sobre os reviews · **Tom:** CNV completa · **Canal:** Slack DM
```
Oi, [nome]. Nos meus PRs recentes, a primeira revisão tem levado cerca de uma semana, e alguns comentários eram sobre partes que o PR não mexia, como [exemplo]. Isso tem me frustrado, porque segura entregas que já estavam prontas e eu preciso de previsibilidade pra planejar. Topa a gente combinar um prazo pra primeira revisão e manter os comentários no escopo do PR? Se preferir, falamos numa call rápida.
```
**Nota:** coloque em `[exemplo]` um comentário real. Sem ele, a pessoa tende a ler como opinião.

### Discussão técnica que escalou

Rascunho:
> já expliquei 3 vezes que não dá pra usar essa lib, ele continua insistindo, isso é absurdo

Saída:

**Intenção:** destravar discussão técnica · **Tom:** CNV completa · **Canal:** Slack thread
```
Acho que a gente tá rodando em círculo nessa thread, e isso tá me deixando frustrado. Minha preocupação com a [lib] é [motivo concreto], e preciso que a decisão leve isso em conta. Que tal uma call rápida pra decidir e depois registrar aqui?
```
**Nota:** preencha o motivo concreto. Sem ele, a mensagem vira opinião contra opinião.
