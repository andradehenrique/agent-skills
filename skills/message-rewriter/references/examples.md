# Exemplos antes/depois (pt-BR)

Cada exemplo mostra o rascunho do usuário e a saída esperada. Use para calibrar tamanho e dose de cuidado.

---

## Direto

### PR — sugestão de performance

Rascunho:
> essa query ta fazendo 3 chamadas no banco, ta lento, tem que refatorar isso com join

Saída:
```
suggestion: essa query faz 3 idas ao banco por request, o que deve pesar na latência da listagem. Dá pra unificar num JOIN?
```

### PR — nit

Rascunho:
> nome de variavel ruim, data não diz nada

Saída:
```
nitpick (non-blocking): `data` ficou genérico aqui. `candidateApplications` deixaria mais claro o que vem do endpoint.
```

### PR — bloqueante

Rascunho:
> isso aqui vai quebrar se o usuario não tiver empresa, vai dar undefined e estourar a tela inteira

Saída:
```
issue (blocking): quando o usuário não tem `company`, `user.company.id` lança TypeError e derruba a página inteira. Precisa de um guard ou optional chaining antes do merge.
```

### Slack — pedir review

Rascunho:
> oi pessoal tudo bem? alguém consegue revisar meu pr? é pequeno

Saída:
```
Oi, pessoal! Alguém consegue revisar este PR até amanhã? São ~80 linhas, só troca o componente de filtro da listagem de vagas: [link]
```

### Slack — bug em produção

Rascunho:
> gente o login com sso ta quebrado em prod, ta dando 500 pra todo mundo que usa google, vi no sentry

Saída:
```
:rotating_light: Login via SSO Google está retornando 500 em produção para todos os usuários desde [horário]. Erro no Sentry: [link]. Alguém do time de [Plataforma/Auth] consegue olhar? Posso ajudar a investigar.
```

---

## Colaborativo

### Discordar de abordagem no PR

Rascunho:
> não concordo com usar redux pra isso, é um estado local, ta complicando à toa

Saída:
```
question: esse estado parece usado só dentro do modal. Tem algum consumidor fora dele que eu não vi? Se não tiver, um `useState` local deixaria o fluxo mais simples e evitaria as 3 actions novas.
```

### Cobrar prazo

Rascunho:
> e aí, cadê aquele endpoint? era pra ontem e eu to travado

Saída:
```
Oi, [nome]! Sobre o endpoint de [X] que a gente combinou pra ontem: tô travado no front esperando ele. Consegue me passar uma previsão? Se ajudar, posso seguir com mock enquanto isso.
```

### Dizer não

Rascunho:
> não vou conseguir pegar isso essa sprint, to cheio

Saída:
```
Essa sprint não consigo pegar: tô com [X] e [Y], que fecham na sexta. Consigo olhar a partir da próxima, ou posso ajudar alguém que pegue agora com contexto.
```

### Apontar erro de alguém (canal público)

Rascunho:
> o fulano subiu sem rodar a migration e quebrou o checkout de novo

Saída:
```
O deploy das 14h subiu sem a migration `add_payment_status`, e o checkout ficou fora por ~20 min. Já rodamos manualmente e normalizou. Proponho a gente incluir a migration no checklist de release pra não repetir.
```
Nota: "de novo" e o nome da pessoa saíram de propósito. Se for um padrão recorrente, vale conversar com a pessoa em DM.

---

## CNV completa

### Feedback de comportamento (DM)

Rascunho:
> toda vez que eu abro pr o ciclano demora uma semana pra revisar e ainda reclama de coisa que não tem nada a ver, to de saco cheio

Saída:
```
Oi, [nome], queria conversar sobre os reviews. Nos meus últimos três PRs, a primeira revisão chegou depois de 5 a 7 dias, e alguns comentários eram sobre partes que o PR não mexia. Tenho ficado frustrado, porque isso tem atrasado entregas que já estavam prontas e eu preciso de previsibilidade pra planejar a sprint. Topa a gente combinar um prazo de review e focar os comentários no escopo do PR? Se preferir, a gente fala numa call rápida.
```

### Discussão técnica que escalou

Rascunho:
> já expliquei 3 vezes que não dá pra usar essa lib, ele continua insistindo, isso é absurdo

Saída:
```
Acho que a gente tá rodando em círculo nessa thread, e isso tá me deixando frustrado. Minha preocupação com a [lib] é [motivo concreto: licença / bundle / manutenção], e preciso que a decisão leve isso em conta. Que tal a gente fazer 15 min de call hoje e registrar a decisão aqui depois?
```
Nota: preencha o motivo concreto; sem ele a mensagem vira opinião contra opinião.
