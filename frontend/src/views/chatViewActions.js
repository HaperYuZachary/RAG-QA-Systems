export async function submitQuestionAndRefreshConversations({
  chatStore,
  kbId,
  question,
}) {
  await chatStore.ask({
    kbId,
    question,
  })

  await chatStore.loadConversations(kbId)
}
