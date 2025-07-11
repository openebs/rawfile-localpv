let
  sources = import ./nix/sources.nix;
  pkgs = import sources.nixpkgs {};
  inherit (pkgs) lib stdenv;
in
pkgs.mkShell {
  name = "rawfile-shell";
  HELM_DOCS_SKIP_VERSION_FOOTER = "true";
  buildInputs = with pkgs; [
    kubectl
    kubernetes-helm-wrapped
    helm-docs
    nixos-shell
    kind
    git
    python313
    poetry # Python3.13 is not supported (Overriding python3 input will not work)
    gcc
    gnumake
    btrfs-progs
    stdenv.cc.cc.lib
  ] ++ pkgs.lib.optional (builtins.getEnv "IN_NIX_SHELL" == "pure") [ docker-client ];
  shellHook = ''
    export LD_PRELOAD=${lib.makeLibraryPath [pkgs.stdenv.cc.cc]}/libstdc++.so.6:$LD_PRELOAD
    poetry env use "$(which python)"
    poetry install
    export PYTHONPATH="$(git rev-parse --show-toplevel)/rawfile:$PYTHONPATH"
    source $(poetry env info -p)/bin/activate
    if ! [ "$CI" == "1" ]; then
      pre-commit install
    fi
  '';
  postShellHook = ''
    deactivate
    unset PYTHONPATH
    unset LD_PRELOAD
  '';
}
