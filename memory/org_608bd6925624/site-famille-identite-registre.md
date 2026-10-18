---
name: site-famille-identite-registre
tags: site-famille,rbac,pragma
updatedAt: 1792360115786
---
Un plugin pragma ne peut pas lire le rôle de l'appelant (IRbacService.h n'expose aucune lecture de rôle). McpServer injecte `_username` et `_is_admin` (McpServer.cpp l. 586-596). Décision de la spec site-famille v1.1 : registre `<racineFamille>/enfants.json` (compte → hôte, utilisateur Linux). Les plugins enfant (TuteurPlugin, KidChatPlugin) prennent l'élève dans `_username`. Les plugins parent exigent l'argument `enfant`, clé du registre. Les rôles enfant et parent ont des plugins disjoints. Un plugin absent de la carte d'un rôle est refusé (resolveEffectivePlugins). Les outils rbac_* sont exemptés (isRbacTool). Ne pas utiliser `theme_set` pour une préférence enfant : il diffuse le thème à tous les clients.