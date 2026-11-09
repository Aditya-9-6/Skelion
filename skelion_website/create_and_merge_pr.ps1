$remote = (git -C "g:/My Drive/helios/skelion_website" remote get-url origin)
if ($remote -match "x-access-token:([^@]+)@") {
  $token = $matches[1]
  $owner = "Aditya-9-6"
  $repo = "Skelion_website"
  $head = "github-integration-20261107221536"
  $base = "main"
  $prBody = @{ title = "feat: full GitHub integration (repos, issues, PRs) with owner handling and fine-grained PAT support"; head = $head; base = $base; body = "This PR adds full GitHub integration, owner handling, fine-grained PAT support, issue/PR UI, and tests." } | ConvertTo-Json -Compress
  $headers = @{ Authorization = "Bearer $token"; "User-Agent" = "Antigravity"; "X-GitHub-Api-Version" = "2022-11-28"; Accept = "application/vnd.github+json" }
  $prResponse = Invoke-RestMethod -Method POST -Uri "https://api.github.com/repos/$owner/$repo/pulls" -Headers $headers -Body $prBody
  $prNumber = $prResponse.number
  Write-Output "PR Number: $prNumber"
  $mergeBody = @{ commit_message = "Merge PR via Antigravity automation" } | ConvertTo-Json -Compress
  $mergeResponse = Invoke-RestMethod -Method PUT -Uri "https://api.github.com/repos/$owner/$repo/pulls/$prNumber/merge" -Headers $headers -Body $mergeBody
  Write-Output "Merged: $($mergeResponse.merged)"
} else {
  Write-Error "Token not found in remote URL"
}