# Sublime Text 2 (CQ) VLT Plugin

It's a plugin that integrates Sublime with Adobe CRX/CQ content.
It makes every-day work way much faster as you can `ctrl+s` in Sublime and `F5` at your CQ page, without time-consuming builds, deploys, or lunching heavy CRXDE.

List of supported commands:

- *add*: single file, batch, interactive add
- *status*: colorful, interactive with diff, single file, batch, entire folder/repo
- *commit*: single file, batch, entire folder/repo
- *update*: single file, batch, entire folder/repo
- *remove*: single file, batch, entire folder
- *revert*: files interactively
- *resolve*: single file
- **rename** - it's not a VLT command, but plugin does copy+add+remove



> Maintained by [Tomek Wytrębowicz](https://github.com/tomalec).

Available at https://github.com/tomalec/Sublime-Text-2-Vlt-Plugin

## Usage

All you need is already checked out repo. 

    vlt --credentials admin:admin co http://localhost:4502/crx/-/jcr:root/apps/myApp .

All commands should work for all files under your repo root directory.

### add

 * By default it should try to auto-add file on save,
 * `ctrl+shift+p` -> `vlt: Add` - adds currently opened file,
 * `ctrl+shift+p` -> `vlt: Add...` - opens panel with (filtered) files and folder from entire repo, to be added interactively,
 * right click on side menu -> `vlt` -> `add (& commit)` - adds (& commits) selected files and folders, prints detailed output in new tab

![Add file demo](http://tomalec.github.io/Sublime-Text-2-Vlt-Plugin/demo/images/add.gif)
![Interactive add demo](http://tomalec.github.io/Sublime-Text-2-Vlt-Plugin/demo/images/add...gif)
![Add from side bar demo](http://tomalec.github.io/Sublime-Text-2-Vlt-Plugin/demo/images/add-side.gif)


### commit

 * By default it should try to auto-commit file on save,
 * `ctrl+shift+p` -> `vlt: Commit` - adds currently opened file,
 * right click on side menu -> `vlt` -> `commit` - commits selected items, prints detailed output in new tab.

![Auto-commit demo](http://tomalec.github.io/Sublime-Text-2-Vlt-Plugin/demo/images/commit-auto.gif)

### status

 * `ctrl+shift+p` -> `vlt: Status` - opens panel with `vlt status` results for entire repo, where you can open new/conflicted files, or diff for modified ones,
 * right click on side menu -> `vlt` -> `add status` - opens new tab with `vlt status` results for selected items.

![Status demo](http://tomalec.github.io/Sublime-Text-2-Vlt-Plugin/demo/images/status.gif)

### update

 * `ctrl+shift+p` -> `vlt: Update` - updates currently opened file,
 * `ctrl+shift+p` -> `vlt: Update All` - updates entire repo,
 * `ctrl+shift+p` -> `vlt: (Repo) Force Update All` - updates entire repo with `--force`,
 * right click on side menu -> `vlt` -> `add update` - updates selected items, prints detailed output in new tab.

![Update file demo](http://tomalec.github.io/Sublime-Text-2-Vlt-Plugin/demo/images/update.gif)
![Update all demo](http://tomalec.github.io/Sublime-Text-2-Vlt-Plugin/demo/images/update-all.gif)

### remove

 * `ctrl+shift+p` -> `vlt: Remove` - updates currently opened file,
 * right click on side menu -> `vlt` -> `add remove (& commit)` - removes (& commits) selected items, prints detailed output in new tab.

### revert

 * `ctrl+shift+p` -> `vlt: Revert...` - opens panel with modified files, that could be reverted.

### resolve

 * `ctrl+shift+p` -> `vlt: Resolve` - marks currently opened file as resolved, so it could be committed afterwards

![Resolve demo](http://tomalec.github.io/Sublime-Text-2-Vlt-Plugin/demo/images/resolve.gif)

### rename

 * `ctrl+shift+p` -> `vlt: Rename...` - prompts for new name, performs file-system copy, `vlt add new`, `vlt commit new`, `vlt remove old`.

![Rename demo](http://tomalec.github.io/Sublime-Text-2-Vlt-Plugin/demo/images/rename.gif)


## Settings

Key  				| Default            | Description
---        			| ---                | ---
`vlt_auto_commit`   | *true*             | If set to true, `ctrl+s` will automatically calls commit.
`vlt_auto_add`      | *true*  	   		 | If set to true, `ctrl+s` in new file will automatically call add, and commit.
`vlt_command`       | *false*  	   		 | Path to vlt binary (if not in PATH). Use `^` to escape spaces and `()`.


## License

[MIT License](http://opensource.org/licenses/MIT) © Tomek Wytrebowicz