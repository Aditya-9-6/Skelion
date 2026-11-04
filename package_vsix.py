import os
import zipfile
import shutil

CONV_ID = "b1faa519-83ae-42f2-9fa8-65bfb5c1b076"
SRC_DIR = r"g:\My Drive\helios\skelion_vscode_extension"
BRAIN_DIR = (
    rf"C:\Users\adity\.gemini\antigravity\brain\{CONV_ID}\skelion_vscode_extension"
)
OUT_VSIX = os.path.join(SRC_DIR, "skelion-vscode-0.1.2.vsix")
BRAIN_VSIX = os.path.join(BRAIN_DIR, "skelion-vscode-0.1.2.vsix")


def build_vsix():
    print(f"Building VSIX from {SRC_DIR} -> {OUT_VSIX}...")
    os.makedirs(BRAIN_DIR, exist_ok=True)

    # Collect files to pack
    files_to_pack = [
        ("package.json", "extension/package.json"),
        ("media/icon.png", "extension/media/icon.png"),
        ("media/icon.svg", "extension/media/icon.svg"),
        ("media/banner.png", "extension/media/banner.png"),
    ]

    # Recursively pack out/
    out_dir = os.path.join(SRC_DIR, "out")
    if os.path.exists(out_dir):
        for root, _, filenames in os.walk(out_dir):
            for fn in filenames:
                full_path = os.path.join(root, fn)
                rel_path = os.path.relpath(full_path, SRC_DIR)
                files_to_pack.append(
                    (
                        rel_path.replace("\\", "/"),
                        f"extension/{rel_path.replace('\\', '/')}",
                    )
                )

    # Recursively pack fixtures/
    fixtures_dir = os.path.join(SRC_DIR, "fixtures")
    if os.path.exists(fixtures_dir):
        for root, _, filenames in os.walk(fixtures_dir):
            for fn in filenames:
                full_path = os.path.join(root, fn)
                rel_path = os.path.relpath(full_path, SRC_DIR)
                files_to_pack.append(
                    (
                        rel_path.replace("\\", "/"),
                        f"extension/{rel_path.replace('\\', '/')}",
                    )
                )

    # Content types XML
    content_types = """<?xml version="1.0" encoding="utf-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="png" ContentType="image/png" />
  <Default Extension="json" ContentType="application/json" />
  <Default Extension="js" ContentType="application/javascript" />
  <Default Extension="svg" ContentType="image/svg+xml" />
  <Default Extension="map" ContentType="application/json" />
  <Default Extension="vsixmanifest" ContentType="text/xml" />
</Types>"""

    # Manifest XML
    manifest = """<?xml version="1.0" encoding="utf-8"?>
<PackageManifest Version="2.0.0" xmlns="http://schemas.microsoft.com/developer/vsx-schema/2011" xmlns:d="http://schemas.microsoft.com/developer/vsx-schema-design/2011">
  <Metadata>
    <Identity Id="skelion-vscode" Version="0.1.2" Language="en-US" Publisher="AdityaDnyaneshwarDahale" />
    <DisplayName>Skelion Agent</DisplayName>
    <Description xml:space="preserve">Full Autonomous Software Development Platform for VS Code with Universal Plugin &amp; MCP Hub</Description>
    <Tags>AI,DevOps,MCP,ClaudeCode,ChatGPT,AutonomousPlatform</Tags>
    <Categories>AI,Other</Categories>
    <GalleryFlags>Public</GalleryFlags>
    <Icon>extension/media/icon.png</Icon>
    <Properties>
      <Property Id="Microsoft.VisualStudio.Code.Engine" Value="^1.88.0" />
      <Property Id="Microsoft.VisualStudio.Code.ExtensionDependencies" Value="" />
    </Properties>
  </Metadata>
  <Installation>
    <InstallationTarget Id="Microsoft.VisualStudio.Code" />
  </Installation>
  <Dependencies />
  <Assets>
    <Asset Type="Microsoft.VisualStudio.Code.Manifest" Path="extension/package.json" />
    <Asset Type="Microsoft.VisualStudio.Services.Icons.Default" Path="extension/media/icon.png" />
  </Assets>
</PackageManifest>"""

    with zipfile.ZipFile(OUT_VSIX, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types)
        z.writestr("extension.vsixmanifest", manifest)
        for rel_src, target_path in files_to_pack:
            real_src = os.path.join(SRC_DIR, rel_src.replace("/", os.sep))
            if os.path.exists(real_src):
                z.write(real_src, target_path)

    # Sync to brain directory as artifact
    shutil.copyfile(OUT_VSIX, BRAIN_VSIX)
    size = os.path.getsize(OUT_VSIX)
    print(f"VSIX built and copied to {BRAIN_VSIX}")
    print(f"Size: {size} bytes ({len(files_to_pack)} files packed)")


if __name__ == "__main__":
    build_vsix()
